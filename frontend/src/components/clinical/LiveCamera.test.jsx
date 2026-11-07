import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { getLastObservation, getMonitoringStatus } from "../../services/index.js";
import LiveCamera from "./LiveCamera.jsx";

vi.mock("../../services/index.js", () => ({
  getLastObservation: vi.fn(),
  getMonitoringStatus: vi.fn(),
  submitMonitoringFrame: vi.fn(),
}));

const trackStop = vi.fn();

describe("LiveCamera", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    getLastObservation.mockResolvedValue({ observation: { person_present: true, posture: "upright", motion: "slow" } });
    getMonitoringStatus.mockResolvedValue({ counters: { frames: 1, clips: 1 } });
    Object.defineProperty(navigator, "mediaDevices", {
      configurable: true,
      value: { getUserMedia: vi.fn().mockResolvedValue({ getTracks: () => [{ stop: trackStop }] }) },
    });
    vi.spyOn(HTMLMediaElement.prototype, "play").mockResolvedValue();
  });

  afterEach(() => vi.restoreAllMocks());

  const startButton = () => screen.getByRole("button", { name: /start camera/i });

  it("cannot start until a patient is selected, and says why", () => {
    render(<LiveCamera available />);
    expect(startButton().disabled).toBe(true);
    expect(screen.getByText(/Select a patient above/)).toBeTruthy();
  });

  it("asks for the selected patient's observation only", async () => {
    render(<LiveCamera available patientId="A" />);
    expect(startButton().disabled).toBe(false);
    await userEvent.click(startButton());
    await waitFor(() => expect(getLastObservation).toHaveBeenCalledWith("A"));
    await screen.findByText("upright");
  });

  it("stops the camera when the patient changes", async () => {
    const { rerender } = render(<LiveCamera available patientId="A" />);
    await userEvent.click(startButton());
    await screen.findByText("upright");

    rerender(<LiveCamera available patientId="B" />);

    await waitFor(() => expect(trackStop).toHaveBeenCalled());
    expect(screen.queryByText("upright")).toBeNull();
    expect(startButton()).toBeTruthy();
  });
});
