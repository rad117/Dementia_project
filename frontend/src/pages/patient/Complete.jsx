import { useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { CheckCircle2 } from "lucide-react";
import { useAssessment } from "../../app/AssessmentContext.jsx";
import Button from "../../components/common/Button.jsx";

export default function Complete() {
    const navigate = useNavigate();
    const { assessmentId, reset } = useAssessment();

    useEffect(() => {
        if (!assessmentId) {
            navigate("/patient", { replace: true });
        }
    }, [assessmentId, navigate]);

    if (!assessmentId) {
        return null;
    }

    function handleDone() {
        reset();
        navigate("/patient", { replace: true });
    }

    return (
        <div className="memora-flow">
            <div className="memora-complete">
                <div className="memora-complete-icon">
                    <CheckCircle2 size={30} />
                </div>

                <p className="memora-kicker">Assessment</p>

                <h1>Assessment complete</h1>

                <p>Your recording has been saved for clinical review.</p>

                <Button variant="accent" size="lg" onClick={handleDone}>
                    Done
                </Button>
            </div>
        </div>
    );
}