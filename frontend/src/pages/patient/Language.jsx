import { useNavigate } from "react-router-dom";
import { Check } from "lucide-react";
import { useAssessment } from "../../app/AssessmentContext.jsx";
import { supportedLanguages } from "../../data/mockTasks.js";
import Button from "../../components/common/Button.jsx";
import styles from "./Language.module.css";

export default function Language(){const navigate=useNavigate();const {language,setLanguage}=useAssessment();return <div className="memora-flow"><div className="memora-flow-head"><p className="memora-kicker">Assessment · 1 of 4</p><h1>Choose a language</h1><p>Select the language you will use to describe the picture.</p></div><div className={styles.grid}>{supportedLanguages.map(l=><button type="button" key={l.code} className={`${styles.card} ${language?.code===l.code?styles.selected:""}`} onClick={()=>setLanguage(l)} aria-pressed={language?.code===l.code}><span><strong>{l.label}</strong>{l.native&&l.native!==l.label?<small>{l.native}</small>:null}</span>{language?.code===l.code?<Check size={22}/>:null}</button>)}</div><Button variant="accent" size="lg" disabled={!language} className="memora-full-action" onClick={()=>navigate("/patient/instructions")}>Continue</Button></div>}
