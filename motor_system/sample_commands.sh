curl http://localhost:8080/health

curl -X POST http://localhost:8080/cmd \
  -H "Content-Type: text/plain" \
  --data 'V1 GET'

curl -X POST http://localhost:8080/cmd \
  -H "Content-Type: text/plain" \
  --data 'V1 SET FL=40'

curl -X POST http://localhost:8080/cmd \
  -H "Content-Type: text/plain" \
  --data 'V1 SET FL=-40'

curl -X POST http://localhost:8080/cmd \
  -H "Content-Type: text/plain" \
  --data 'V1 STOP'
