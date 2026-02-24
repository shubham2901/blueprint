FROM node:20-slim

WORKDIR /app

# Install dependencies
COPY package.json package-lock.json ./
RUN npm ci

# Copy application code
COPY . .

# Build-time env vars — Next.js bakes these during `npm run build`
ARG NEXT_PUBLIC_API_URL
ENV NEXT_PUBLIC_API_URL=$NEXT_PUBLIC_API_URL

ARG BACKEND_INTERNAL_URL
ENV BACKEND_INTERNAL_URL=$BACKEND_INTERNAL_URL

# Build
RUN npm run build

# Expose port (Railway sets PORT dynamically)
EXPOSE 3000

# Run - use shell form to expand PORT env var
CMD npm start -- -p ${PORT:-3000}
