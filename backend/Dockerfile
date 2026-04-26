# ============================================
# Production Node.js Backend
# ============================================
FROM node:18-alpine

WORKDIR /app

# Copy dependency manifests first (cache layer)
COPY package*.json ./
RUN npm ci --omit=dev

# Copy application source
COPY . .

EXPOSE 5000

HEALTHCHECK --interval=30s --timeout=3s --start-period=15s --retries=3 \
  CMD wget --no-verbose --tries=1 --spider http://localhost:5000/ || exit 1

CMD ["node", "server.js"]
