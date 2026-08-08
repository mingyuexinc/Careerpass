import {
  deliveryProgressMeta,
  getOfferCount,
  isValidDeliveryTransition,
} from "../domain/mappings";

describe("delivery progress rules", () => {
  it("allows the next stage and termination, but prevents skipping stages", () => {
    expect(isValidDeliveryTransition("submitted", "screening")).toBe(true);
    expect(isValidDeliveryTransition("submitted", "interview_1")).toBe(false);
    expect(isValidDeliveryTransition("screening", "terminated")).toBe(true);
    expect(isValidDeliveryTransition("offer", "screening")).toBe(false);
  });

  it("marks terminal labels and counts offers", () => {
    expect(deliveryProgressMeta.offer.terminal).toBe(true);
    expect(deliveryProgressMeta.screening.terminal).toBe(false);
    expect(getOfferCount(["offer", "screening", "offer"])).toBe(2);
  });
});
