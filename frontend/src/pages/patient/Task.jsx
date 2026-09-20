import { useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { Mic } from "lucide-react";
import { useSession } from "../../app/SessionContext.jsx";
import { useAssessment } from "../../app/AssessmentContext.jsx";
import { pictureDescriptionTask } from "../../data/mockTasks.js";
import { createAssessment } from "../../services/index.js";
import PictureStimulus from "../../components/assessment/PictureStimulus.jsx";
import Button from "../../components/common/Button.jsx";

export default function PatientTask(){const {participant}=useSession();const {language,assessmentId,setAssessmentId}=useAssessment();const navigate=useNavigate();useEffect(()=>{if(!language){navigate("/patient/language",{replace:true});return}if(!assessmentId){createAssessment({patientId:participant.patientId,language:language.label,taskId:pictureDescriptionTask.id}).then(a=>setAssessmentId(a.id))}},[language,assessmentId,participant.patientId,navigate,setAssessmentId]);if(!language)return null;return <div className="memora-flow"><div className="memora-flow-head"><div className="memora-meta-row"><p className="memora-kicker">Assessment · 3 of 4</p><span className="memora-step">{language.label}</span></div><h1>Describe the picture</h1><p>Tell us what you see. Take your time.</p></div><div className="memora-task-frame"><PictureStimulus/></div><p className="memora-task-note">There is no need to rush. Speak in your usual way.</p><Button variant="accent" size="lg" className="memora-full-action" disabled={!assessmentId} onClick={()=>navigate("/patient/recording")}><Mic size={21}/>{assessmentId?"Start recording":"Preparing assessment…"}</Button></div>}
