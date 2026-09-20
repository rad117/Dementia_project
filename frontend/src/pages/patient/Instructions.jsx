import { useNavigate } from "react-router-dom";
import { Volume2 } from "lucide-react";
import { useAssessment } from "../../app/AssessmentContext.jsx";
import Button from "../../components/common/Button.jsx";
import styles from "./patientPages.module.css";

export default function Instructions(){const navigate=useNavigate();const {language}=useAssessment();const speak=()=>{if("speechSynthesis" in window){window.speechSynthesis.cancel();const u=new SpeechSynthesisUtterance("Look at the picture. Tell us what you see. Take your time.");u.lang=language?.code||"en-IN";window.speechSynthesis.speak(u)}};return <div className="memora-flow"><div className="memora-flow-head"><p className="memora-kicker">Assessment · 2 of 4</p><h1>Assessment instructions</h1><p>You will describe one picture. There are no right or wrong words.</p></div><ol className={styles.instructionsList}><li>Look at the picture.</li><li>Describe what you see.</li><li>Take your time.</li></ol><div className="memora-secondary-action"><Button variant="secondary" size="lg" onClick={speak}><Volume2 size={19}/>Listen to instructions</Button></div><Button variant="accent" size="lg" className="memora-full-action" onClick={()=>navigate("/patient/task")}>Continue</Button></div>}
