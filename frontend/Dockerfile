FROM node:20-alpine AS base

WORKDIR /app

RUN npm install -g pnpm@9.15.4

COPY package.json ./
RUN pnpm install --ignore-scripts

COPY . .

EXPOSE 5173

CMD ["pnpm", "run", "dev"]
