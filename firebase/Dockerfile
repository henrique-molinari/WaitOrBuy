FROM node:20-bookworm-slim
RUN apt-get update && apt-get install -y --no-install-recommends default-jre-headless curl ca-certificates && apt-get clean
RUN npm install -g firebase-tools@13.29.1
WORKDIR /srv
COPY firebase.json firestore.rules firestore.indexes.json ./
EXPOSE 8080 9099
CMD ["firebase", "emulators:start", "--only", "auth,firestore", "--project", "demo-waitorbuy"]
