# Bottany Infrastructure Add-on

## Folder Structure

k8s/
  deployment.yaml
  service.yaml
  ingress.yaml

helm/
  values.yaml  (Use with Helm to install Prometheus & Grafana)

app/ml/
  anomaly.py   (Isolation Forest model)

---

## How to Use

1️⃣ Upload k8s/ to your GitHub repo root.
2️⃣ Apply with:
   kubectl apply -f k8s/

3️⃣ Install monitoring stack:
   helm install monitoring prometheus-community/kube-prometheus-stack -f helm/values.yaml

4️⃣ Import ML module into your FastAPI app:
   from app.ml.anomaly import OfferAnomalyDetector

5️⃣ Add sklearn to requirements:
   scikit-learn