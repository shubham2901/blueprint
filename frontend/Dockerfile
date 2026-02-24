FROM node:20-slim

WORKDIR /app

# Install dependencies
COPY package.json package-lock.json ./
RUN npm ci

# Copy application code
COPY . .

# Build
RUN npm run build

# Expose port (Railway sets PORT dynamically)
EXPOSE 3000

# Run - Next.js respects PORT env var automatically
CMD ["npm", "start"]
