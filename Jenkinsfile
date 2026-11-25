pipeline {
    agent any

    options {
        timestamps()
    }

    environment {
        IMAGE_NAME = 'alban7s/nexus'
    }

    stages {
        stage('Checkout') {
            steps {
                git branch: 'main',
                    url: 'https://github.com/Alban7s/NEXUS.git'
            }
        }

        stage('Build Docker Image') {
            steps {
                sh '''
                    docker build -t ${IMAGE_NAME}:${BUILD_NUMBER} .
                    docker tag ${IMAGE_NAME}:${BUILD_NUMBER} ${IMAGE_NAME}:latest
                '''
            }
        }

        stage('Push to Docker Hub') {
            steps {
                withCredentials([
                    usernamePassword(
                        credentialsId: 'docker_creds',
                        usernameVariable: 'DOCKER_USER',
                        passwordVariable: 'DOCKER_PASS'
                    )
                ]) {
                    sh '''
                        set +x
                        printf '%s' "$DOCKER_PASS" | docker login \
                            --username "$DOCKER_USER" --password-stdin

                        docker push ${IMAGE_NAME}:${BUILD_NUMBER}
                        docker push ${IMAGE_NAME}:latest

                        docker logout
                    '''
                }
            }
        }

        stage('Deploy to Kubernetes') {
            steps {
                withCredentials([
                    file(credentialsId: 'kubeconfig',
                         variable: 'KUBECONFIG_FILE')
                ]) {
                    sh '''
                        export KUBECONFIG="$KUBECONFIG_FILE"

                        sed "s|image: nexus:latest|image: ${IMAGE_NAME}:${BUILD_NUMBER}|" \
                            k8s/nexus-local.yaml | kubectl apply -f -

                        kubectl rollout status deployment/nexus --timeout=180s
                        kubectl get pods -l app=nexus
                    '''
                }
            }
        }
    }

    post {
        success {
            echo 'NEXUS deployed successfully!'
        }
        failure {
            echo 'Pipeline failed. Check the Jenkins console output.'
        }
    }
}
