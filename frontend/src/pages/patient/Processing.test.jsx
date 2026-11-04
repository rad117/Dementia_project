import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import Processing from "./Processing.jsx";

const { uploadAssessmentAudioMock, getAssessmentResultsMock } = vi.hoisted(() => ({
  uploadAssessmentAudioMock: vi.fn(),
  getAssessmentResultsMock: vi.fn(),
}));

vi.mock("../../services/index.js", () => ({
  uploadAssessmentAudio: uploadAssessmentAudioMock,
  getAssessmentResults: getAssessmentResultsMock,
}));

const navigateMock = vi.fn();
vi.mock("react-router-dom", () => ({ useNavigate: () => navigateMock }));

const setResultsMock = vi.fn();
const useAssessmentMock = vi.fn();
vi.mock("../../app/AssessmentContext.jsx", () => ({
  useAssessment: () => useAssessmentMock(),
}));

const audioBlob = new Blob(["fake-audio"], { type: "audio/webm" });

beforeEach(() => {
  uploadAssessmentAudioMock.mockReset();
  getAssessmentResultsMock.mockReset();
  navigateMock.mockReset();
  setResultsMock.mockReset();
  useAssessmentMock.mockReset();
  useAssessmentMock.mockReturnValue({
    assessmentId: "assess_1",
    audioBlob,
    setResults: setResultsMock,
  });
});

describe("Processing (assessment submission)", () => {
  it("uploads the recording, polls for results, stores them, and advances to complete", async () => {
    uploadAssessmentAudioMock.mockResolvedValue({ id: "assess_1", status: "complete" });
    const results = { assessment: { id: "assess_1" }, features: { riskScore: 0.2 } };
    getAssessmentResultsMock.mockResolvedValue(results);

    render(<Processing />);

    await waitFor(() => expect(navigateMock).toHaveBeenCalledWith("/patient/complete"));
    expect(uploadAssessmentAudioMock).toHaveBeenCalledWith("assess_1", audioBlob);
    expect(setResultsMock).toHaveBeenCalledWith(results);
  });

  it("shows a retry option instead of navigating when the upload fails", async () => {
    uploadAssessmentAudioMock.mockRejectedValue(new Error("Network error. Please check your connection."));

    render(<Processing />);

    expect(await screen.findByText(/network error/i)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /try again/i })).toBeInTheDocument();
    expect(navigateMock).not.toHaveBeenCalledWith("/patient/complete");
    expect(setResultsMock).not.toHaveBeenCalled();
  });

  it("redirects back to the task screen when there is nothing to submit", () => {
    useAssessmentMock.mockReturnValue({ assessmentId: null, audioBlob: null, setResults: setResultsMock });

    render(<Processing />);

    expect(navigateMock).toHaveBeenCalledWith("/patient/task", { replace: true });
    expect(uploadAssessmentAudioMock).not.toHaveBeenCalled();
  });
});
