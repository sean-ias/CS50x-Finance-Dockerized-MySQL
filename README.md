Clone the repo
You should somewhere have legacy MySQL or RDS MySQL for this
Change env vars in Dockerfile for db creds
build image: docker build -t my-fin-image .
run dockerfile: $ docker run -d --name my-fin-app --network host my-fin-image