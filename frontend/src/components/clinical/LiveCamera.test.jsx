import { act, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { getLastObservation, getMonitoringStatus, submitMonitoringFrame } from "../../services/index.js";
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
    await screen.findByText("upright");
    expect(getLastObservation.mock.calls.length).toBeGreaterThan(0);
    expect(getLastObservation.mock.calls.every(([id]) => id === "A")).toBe(true);
  });

  it("releases the camera if the patient changes while it is still starting", async () => {
    let grant;
    navigator.mediaDevices.getUserMedia.mockReturnValueOnce(new Promise((resolve) => (grant = resolve)));
    const { rerender } = render(<LiveCamera available patientId="A" />);
    await userEvent.click(startButton());

    rerender(<LiveCamera available patientId="B" />);
    await act(async () => grant({ getTracks: () => [{ stop: trackStop }] }));

    expect(trackStop).toHaveBeenCalled();
    expect(screen.queryByText("LIVE")).toBeNull();
    expect(HTMLMediaElement.prototype.play).not.toHaveBeenCalled();
  });

  describe("frames being encoded", () => {
    let finishEncoding;

    beforeEach(() => {
      vi.spyOn(HTMLVideoElement.prototype, "videoWidth", "get").mockReturnValue(640);
      vi.spyOn(HTMLVideoElement.prototype, "videoHeight", "get").mockReturnValue(480);
      vi.spyOn(HTMLCanvasElement.prototype, "getContext").mockReturnValue({ drawImage: vi.fn() });
      vi.spyOn(HTMLCanvasElement.prototype, "toBlob").mockImplementation((cb) => {
        finishEncoding = cb;
      });
      submitMonitoringFrame.mockResolvedValue({ status: "ok" });
    });

    const encodingStarted = async () => {
      await waitFor(() => expect(HTMLCanvasElement.prototype.toBlob).toHaveBeenCalled(), { timeout: 2000 });
    };

    it("are filed under the patient they were captured for", async () => {
      render(<LiveCamera available patientId="A" />);
      await userEvent.click(startButton());
      await encodingStarted();
      const blob = new Blob(["x"]);
      await act(async () => finishEncoding(blob));
      expect(submitMonitoringFrame).toHaveBeenCalledTimes(1);
      expect(submitMonitoringFrame).toHaveBeenCalledWith(blob, "A");
    });

    it("are dropped if the patient changed before encoding finished", async () => {
      const { rerender } = render(<LiveCamera available patientId="A" />);
      await userEvent.click(startButton());
      await encodingStarted();

      rerender(<LiveCamera available patientId="B" />);
      await act(async () => finishEncoding(new Blob(["x"])));

      expect(submitMonitoringFrame).not.toHaveBeenCalled();
    });
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
