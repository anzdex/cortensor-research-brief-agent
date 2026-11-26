#!/usr/bin/env bash
# Convenience runner: creates the venv, installs deps, runs the brief agent.
# Usage: ./run.sh "Your topic" [--out outputs/x.md]
# Env: OPENMINION_PROVIDER (default ollama), OPENMINION_MODEL,
#      provider API keys (see .env.example) — never commit .env.
set -euo pipefail
cd "$(dirname "$0")"

# Workaround: httpx (used by OpenMinion's providers, trust_env=True) fails on
# bracketed IPv6 literals in no_proxy, e.g. [::1] -> "InvalidURL: Invalid
# port: ':1]'". Strip bracketed entries; bare IPv6 forms still work, and
# localhost/127.0.0.1 are kept so the local Ollama server is never proxied.
sanitize_no_proxy() {
  local value="$1" out="" part
  IFS=',' read -r -a parts <<< "$value"
  for part in "${parts[@]}"; do
    case "$part" in
      \[*\]) ;;
      *) out="${out:+$out,}$part" ;;
    esac
  done
  printf '%s' "$out"
}
for var in no_proxy NO_PROXY; do
  current="${!var:-}"
  if [ -n "$current" ]; then
    cleaned="$(sanitize_no_proxy "$current")"
    case ",$cleaned," in *,localhost,*) ;; *) cleaned="${cleaned:+$cleaned,}localhost" ;; esac
    case ",$cleaned," in *,127.0.0.1,*) ;; *) cleaned="${cleaned:+$cleaned,}127.0.0.1" ;; esac
    export "$var=$cleaned"
  fi
done

if [ ! -d .venv ]; then
  python3 -m venv .venv
fi
.venv/bin/pip install --quiet -r requirements.txt

if [ "${OPENMINION_PROVIDER:-ollama}" = "ollama" ]; then
  if ! curl -fsS -m 3 http://127.0.0.1:11434/api/tags >/dev/null 2>&1; then
    echo "Ollama is not running. Start it first, then pull a model:"
    echo "  ollama serve   # in another terminal"
    echo "  ollama pull llama3.2:1b"
    exit 1
  fi
fi

export OPENMINION_HOME="$PWD/.openminion-home"
exec .venv/bin/python main.py "$@"
