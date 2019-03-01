# OSCAR Worker

[![Docker Build Status](https://img.shields.io/docker/build/grycap/oscar-worker.svg)](https://hub.docker.com/r/grycap/oscar-worker/) [![License](https://img.shields.io/badge/license-Apache%202-blue.svg)](https://www.apache.org/licenses/LICENSE-2.0)

OSCAR Worker is the default queue worker for [OpenFaaS](https://github.com/openfaas/faas) in the [OSCAR framework](https://github.com/grycap/oscar). It enables launching long-running functions as Kubernetes Jobs when `/async-function/` path is used to make requests.

The goal is to ensure that each invocation has the specified resources and, furthermore, that functions can be executed in parallel depending on the resources available in the cluster.

![openfaas async worker](https://user-images.githubusercontent.com/18619097/53635212-ae263080-3c1c-11e9-948b-338291c428e8.png)

## Configuration

You can configure the worker through environment variables. To modify the default values you can edit the `oscar-worker-dep.yaml` file:

```yaml
...
        env:
        # Token to access the k8s API server (if not set reads the content of '/var/run/secrets/kubernetes.io/serviceaccount/token')  
        # - name: KUBE_TOKEN
        #   value: "xxx"
        - name: KUBERNETES_SERVICE_HOST
          value: "kubernetes.default"
        - name: KUBERNETES_SERVICE_PORT
          value: "443"
        - name: NATS_ADDRESS
          value: "nats.openfaas"
        - name: NATS_PORT
          value: "4222"
        - name: JOB_TTL_SECONDS_AFTER_FINISHED
          value: 60
        - name: JOB_BACKOFF_LIMIT
          value: 3
...
```

## Deployment

In order to deploy the OSCAR Worker you need to have already installed OpenFaaS in the Kubernetes cluster. Then, delete the [nats-queue-worker](https://github.com/openfaas/nats-queue-worker/) deployment:

```bash
kubectl delete deploy queue-worker -n openfaas
```

And create the required namespaces, RBAC and deployment:

```bash
kubectl apply -f yaml/oscar-worker-namespaces.yaml
kubectl apply -f yaml/oscar-worker-rbac.yaml
kubectl apply -f yaml/oscar-worker-dep.yaml
```

## Logs

If you want to inspect worker's logs run:

```bash
kubectl logs deploy/oscar-worker -n oscar
```

To see specific function invocation logs, first get all pods of the `oscar-fn` namespace and then query the one you want:

```bash
kubectl get pods -n oscar-fn
kubectl logs POD_NAME -n oscar-fn
```

## Clear completed Jobs

Completed Jobs can be automatically deleted after finishing by enabling the `TTLAfterFinished` feature gate of Kubernetes versions >= `v1.12`. TTL Seconds to clean up Jobs can be configured through the `JOB_TTL_SECONDS_AFTER_FINISHED` environment variable of the worker.

To delete completed jobs manually, execute:

```bash
kubectl delete job $(kubectl get job -o=jsonpath='{.items[?(@.status.succeeded==1)].metadata.name}' -n oscar-fn) -n oscar-fn
```