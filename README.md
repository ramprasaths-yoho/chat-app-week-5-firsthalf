# AI Chat App - Part 1 (backend)

## Run
```bash
git checkout -b feature/chat-app
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env            # add your OPENAI_API_KEY
docker compose up -d            # PostgreSQL
uvicorn app.main:app --reload
pytest -q
```

## Try it with curl
```bash
KEY=dev-key-1
SID=$(curl -s -X POST localhost:8000/sessions -H "X-API-Key: $KEY" | python -c "import sys,json;print(json.load(sys.stdin)['id'])")

# streaming (-N disables curl buffering)
curl -N -X POST localhost:8000/sessions/$SID/chat \
  -H "X-API-Key: $KEY" -H "Content-Type: application/json" \
  -d '{"message":"My name is Ram. Remember it."}'

# second session must NOT know the name
SID2=$(curl -s -X POST localhost:8000/sessions -H "X-API-Key: $KEY" | python -c "import sys,json;print(json.load(sys.stdin)['id'])")
curl -N -X POST localhost:8000/sessions/$SID2/chat \
  -H "X-API-Key: $KEY" -H "Content-Type: application/json" \
  -d '{"message":"What is my name?"}'

curl -s localhost:8000/sessions/$SID/messages -H "X-API-Key: $KEY"
curl -s localhost:8000/sessions/$SID -H "X-API-Key: $KEY"      # tokens + cost
curl -s localhost:8000/usage -H "X-API-Key: $KEY"              # bonus

# rate limit: 21st message -> 429
for i in $(seq 1 21); do
  curl -s -o /dev/null -w "$i -> %{http_code}\n" -X POST localhost:8000/sessions/$SID/chat \
    -H "X-API-Key: $KEY" -H "Content-Type: application/json" -d '{"message":"hi"}'
done
curl -i -X POST localhost:8000/sessions/$SID/chat -H "X-API-Key: $KEY" \
  -H "Content-Type: application/json" -d '{"message":"hi"}'   # shows Retry-After
```

## Screenshot of DB rows
```bash
docker compose exec db psql -U postgres chatapp -c "SELECT id, session_id, role, left(content,40), tokens, created_at FROM messages ORDER BY id;"
```
