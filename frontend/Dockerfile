FROM node:22-alpine

WORKDIR /app

# Install dependencies first so Docker can cache this layer between builds.
COPY package.json package-lock.json ./
RUN npm ci

# Copy the app into the image. docker-compose also bind-mounts the frontend
# folder during local development so edits show up without rebuilding.
COPY . .

EXPOSE 3000

CMD ["npm", "run", "dev", "--", "--hostname", "0.0.0.0", "--port", "3000"]
