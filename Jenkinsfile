caughtError = 0

try {

    node {

      stage('Entering Build Container') {
          withCredentials([[$class: 'UsernamePasswordMultiBinding', credentialsId: 'jenkins_build_jumpcloud',
                usernameVariable: 'ARTIFACTORY_USER', passwordVariable: 'ARTIFACTORY_PASSWORD']]) {

                  // Checks out code and submodules
                  // https://stackoverflow.com/a/41639591
                  checkout([
                    $class: 'GitSCM',
                    branches: scm.branches,
                    extensions: scm.extensions + [
                      [
                        $class: 'SubmoduleOption',
                        parentCredentials: true,
                        disableSubmodules: false,
                        recursiveSubmodules: true,
                        trackingSubmodules: false
                      ],
                      [
                        $class: 'CloneOption',
                        noTags: false,
                        shallow: false,
                        depth: 0,
                        reference: ''
                      ]
                    ],
                    userRemoteConfigs: scm.userRemoteConfigs
                  ])

                docker.image("bossanova-cloud-container.jfrog.io/build-images/python-build:0.0.2").inside("-u root") {

                  testPython {
                    excludeTestKind =  "GPU"
                    artifactoryPassword = "${ARTIFACTORY_PASSWORD}"
                    artifactoryUser = "${ARTIFACTORY_USER}"
                  }


                  publishWheel {
                    artifactoryPattern = "cloud_oos_detection-*-py2-none-any.whl"
                    artifactoryTarget =  "cloud_oos_detection"
                  }
                
                }
          }
        }
    }
  }

catch(caughtError){
  currentBuild.result = "FAILURE"
  echo 'Build failed with Error: ' + caughtError.toString()
  caughtError = caughtError

}
finally{
    node {

        stage("Cleanup Workspace") {
            step([$class: 'WsCleanup'])
        }


        if (caughtError != 0) {
          throw caughtError
        }
      }

}
