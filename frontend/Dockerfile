FROM node:20-alpine AS builder

WORKDIR /app

# Copy package.json and package-lock.json
COPY package*.json ./
# Use --no-optional to avoid macos specific lightningcss issues on linux
RUN npm ci --no-optional

# Copy the rest of the application
COPY . .

# Build the Next.js application
RUN npm run build

# Production image
FROM node:20-alpine AS runner

WORKDIR /app

ENV NODE_ENV=production

# Copy built files
COPY --from=builder /app/next.config.ts ./
COPY --from=builder /app/public ./public
# Note: Ensure next.config.ts has output: 'standalone' if using this Dockerfile
COPY --from=builder /app/.next/standalone ./
COPY --from=builder /app/.next/static ./.next/static

EXPOSE 3000

# Start command
CMD ["node", "server.js"]
