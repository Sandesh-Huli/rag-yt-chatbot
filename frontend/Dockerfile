# ============================================
# Stage 1: Build the Vite React application
# ============================================
FROM node:18-alpine AS builder

WORKDIR /app

# Accept build arguments
ARG VITE_BACKEND_URI
ARG VITE_AUTH_BACKEND_URI

# Set as environment variables for Vite
ENV VITE_BACKEND_URI=$VITE_BACKEND_URI
ENV VITE_AUTH_BACKEND_URI=$VITE_AUTH_BACKEND_URI

# Copy dependency manifests first (cache layer)
COPY package*.json ./
RUN npm ci

# Copy source and build
COPY . .
RUN npm run build

# ============================================
# Stage 2: Serve with lightweight static server
# ============================================
FROM node:18-alpine AS production

WORKDIR /app

RUN npm install -g serve@latest

# Copy only the built output from builder
COPY --from=builder /app/dist ./dist

EXPOSE 3000

RUN addgroup -S appgroup && adduser -S appuser -G appgroup
USER appuser

HEALTHCHECK --interval=30s --timeout=3s --start-period=10s --retries=3 \
  CMD wget --no-verbose --tries=1 --spider http://localhost:3000/ || exit 1

CMD ["serve", "-s", "dist", "-l", "3000"]
