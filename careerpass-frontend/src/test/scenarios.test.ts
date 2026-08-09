import { createRunningSnapshot } from "../api/mock/fixtures/scenarios";

describe("mock running scenario", () => {
  it("keeps one conversation for every seeded application", () => {
    const snapshot = createRunningSnapshot();

    expect(snapshot.conversations).toHaveLength(snapshot.applications.length);
    expect(
      snapshot.conversations.map((conversation) => conversation.applicationId),
    ).toEqual(snapshot.applications.map((application) => application.id));
  });
});
