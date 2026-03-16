FROM node:20-alpine

WORKDIR /app

COPY package*.json ./
RUN npm install

COPY . .

RUN npm run build

# Next standalone server serves static assets from
# .next/standalone/.next/static at runtime.
RUN mkdir -p .next/standalone/.next \
    && cp -R .next/static .next/standalone/.next/static \
    && if [ -d public ]; then cp -R public .next/standalone/public; fi

EXPOSE 3000

CMD ["npm", "run", "start"]
