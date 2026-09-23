import { pictureDescriptionTask } from "../../data/mockTasks.js";
import stimulusImage from "../../assets/stimuli/picture-description.jpg";
import styles from "./PictureStimulus.module.css";

export default function PictureStimulus() {
  return (
    <div className={styles.frame}>
      <img src={stimulusImage} alt={pictureDescriptionTask.imageAlt} className={styles.image} />
    </div>
  );
}
