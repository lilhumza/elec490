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

curl -X POST http://localhost:8080/cmd \
  -H "Content-Type: text/plain" \
  --data 'V1 SET FL=30 FR=30 RL=30 RR=30'

curl -X POST http://localhost:8080/cmd \
  -H "Content-Type: text/plain" \
  --data 'V1 SET RL=-40 RR=-40'
