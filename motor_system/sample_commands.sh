# -------------------------
# Health + state
# -------------------------
curl http://localhost:8080/health

curl -X POST http://localhost:8080/cmd \
  -H "Content-Type: text/plain" \
  --data 'V1 GET'

# -------------------------
# Pumps (individual + grouped)
# -------------------------
curl -X POST http://localhost:8080/cmd \
  -H "Content-Type: text/plain" \
  --data 'V1 SET FL=40'

curl -X POST http://localhost:8080/cmd \
  -H "Content-Type: text/plain" \
  --data 'V1 SET FR=-60'

curl -X POST http://localhost:8080/cmd \
  -H "Content-Type: text/plain" \
  --data 'V1 STOP'

curl -X POST http://localhost:8080/cmd \
  -H "Content-Type: text/plain" \
  --data 'V1 SET FL=30 FR=30 RL=30 RR=30'

curl -X POST http://localhost:8080/cmd \
  -H "Content-Type: text/plain" \
  --data 'V1 SET RL=-40 RR=-40'

# -------------------------
# Actuator (syringe control)
# -------------------------

# Home actuator (retract fully, define ACT_POS=0)
curl -X POST http://localhost:8080/cmd \
  -H "Content-Type: text/plain" \
  --data 'V1 ACT HOME'

# Extend fully (100%)
curl -X POST http://localhost:8080/cmd \
  -H "Content-Type: text/plain" \
  --data 'V1 ACT GOTO=100'

# Move to mid-stroke (~50%)
curl -X POST http://localhost:8080/cmd \
  -H "Content-Type: text/plain" \
  --data 'V1 ACT GOTO=50'

# Small retraction (~10%)
curl -X POST http://localhost:8080/cmd \
  -H "Content-Type: text/plain" \
  --data 'V1 ACT GOTO=10'

# Stop actuator immediately (safe abort)
curl -X POST http://localhost:8080/cmd \
  -H "Content-Type: text/plain" \
  --data 'V1 ACT STOP'

# -------------------------
# Combined example (pumps + actuator)
# -------------------------

# Start pumps forward, then dispense to 30%
curl -X POST http://localhost:8080/cmd \
  -H "Content-Type: text/plain" \
  --data 'V1 SET FL=25 FR=25 RL=25 RR=25'

curl -X POST http://localhost:8080/cmd \
  -H "Content-Type: text/plain" \
  --data 'V1 ACT GOTO=30'

# Stop everything
curl -X POST http://localhost:8080/cmd \
  -H "Content-Type: text/plain" \
  --data 'V1 STOP'
