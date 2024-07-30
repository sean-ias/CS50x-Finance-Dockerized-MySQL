Clone the repo<br>
You should somewhere have legacy MySQL or RDS MySQL for this<br>
Change env vars in Dockerfile for db creds<br>
build image: docker build -t my-fin-image .<br>
run dockerfile: $ docker run -d --name my-fin-app --network host my-fin-image<br>
