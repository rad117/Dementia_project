import FeatureSection from "../../components/clinical/FeatureSection.jsx";
import Bezel from "../../components/common/Bezel.jsx";
import FadeInUp from "../../components/motion/FadeInUp.jsx";

export default function ClinicalModelInfo() {
  return (
    <div>
      <h1 style={{ fontSize: 26, marginBottom: 20 }}>Model information</h1>
      <FadeInUp>
        <Bezel innerClassName="p-5">
          <FeatureSection
            bare
            title="Current screening model"
            items={[
              { label: "Model version", value: "baseline_v2" },
              { label: "Analysis pipeline", value: "Acoustic + ASR + NLP fusion" },
              { label: "Task", value: "Picture Description" },
              { label: "Status", value: "Research baseline" },
            ]}
            footnote="Evaluation metrics (sensitivity, specificity, ROC-AUC, language and task breakdowns) live alongside the trained model artifacts in models/baseline_v2/metrics.json and will be surfaced here directly from the backend in a future pass."
          />
        </Bezel>
      </FadeInUp>
    </div>
  );
}
