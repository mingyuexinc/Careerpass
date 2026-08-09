import {
  deliveryProgressMeta,
  getOfferCount,
  isValidDeliveryTransition,
} from "../domain/mappings";

describe("delivery progress rules", () => {
  it("allows forward jumps and termination, but prevents backward changes", () => {
    expect(isValidDeliveryTransition("submitted", "screening")).toBe(true);
    expect(isValidDeliveryTransition("submitted", "interview_1")).toBe(true);
    expect(isValidDeliveryTransition("screening", "offer")).toBe(true);
    expect(isValidDeliveryTransition("screening", "terminated")).toBe(true);
    expect(isValidDeliveryTransition("interview_1", "screening")).toBe(false);
    expect(isValidDeliveryTransition("offer", "screening")).toBe(false);
  });

  it("marks terminal labels and counts offers", () => {
    expect(deliveryProgressMeta.offer.terminal).toBe(true);
    expect(deliveryProgressMeta.screening.terminal).toBe(false);
    expect(getOfferCount(["offer", "screening", "offer"])).toBe(2);
  });
});
