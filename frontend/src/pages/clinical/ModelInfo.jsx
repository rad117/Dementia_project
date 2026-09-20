import FeatureSection from "../../components/clinical/FeatureSection.jsx";

export default function ClinicalModelInfo() {
  return (
    <div>
      <h1 style={{ fontSize: 26, marginBottom: 20 }}>Model information</h1>
      <FeatureSection
        title="Current screening model"
        items={[
          { label: "Model version", value: "screening-v0.1-demo" },
          { label: "Analysis pipeline version", value: "demo-v0.1" },
          { label: "Task", value: "Picture Description" },
          { label: "Status", value: "Demo / illustrative" },
        ]}
        footnote="This is a frontend demo shell. Real model versioning, evaluation metrics (sensitivity, specificity, ROC-AUC, language and task breakdowns) and inference metadata are owned by the backend/research team and will be surfaced here once available."
      />
    </div>
  );
}
