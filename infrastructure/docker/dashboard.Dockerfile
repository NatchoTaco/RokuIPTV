FROM node:22-slim

WORKDIR /app/apps/dashboard

COPY apps/dashboard/package.json /app/apps/dashboard/package.json
RUN npm install

COPY apps/dashboard /app/apps/dashboard

EXPOSE 5173

CMD ["npm", "run", "dev"]
