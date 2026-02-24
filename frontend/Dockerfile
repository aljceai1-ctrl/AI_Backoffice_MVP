FROM node:20-alpine

WORKDIR /app

# Install dependencies first (cached layer)
COPY package.json ./
RUN npm install --legacy-peer-deps

# Copy source code
COPY . .

EXPOSE 3000

# Dev mode: hot-reload, no build step required
CMD ["npm", "run", "dev"]
