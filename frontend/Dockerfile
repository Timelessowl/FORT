FROM node:18-alpine

WORKDIR /app/fort

COPY fort/package*.json ./
RUN npm install

COPY fort/ .
EXPOSE 3000

CMD ["npm", "run", "dev"]

