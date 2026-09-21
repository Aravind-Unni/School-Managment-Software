import { describe, expect, it } from "vitest";
import {
  cellKey,
  clashFor,
  gridFromSlots,
  reassignTeacher,
  slotsFromGrid,
  subjectLoad,
  teacherLoad,
  weekShape,
} from "@features/timetable/plannerModel";
import { subjectColour } from "@features/timetable/subjectColours";

const slots = [
  { section_id: "A", day_of_week: 1, slot_code: "P1", subject_id: "math", teacher_id: "t1" },
  { section_id: "A", day_of_week: 1, slot_code: "P2", subject_id: "eng", teacher_id: "t2" },
  { section_id: "B", day_of_week: 1, slot_code: "P1", subject_id: "math", teacher_id: "t1" },
];

describe("planner model", () => {
  it("round-trips slots through the grid", () => {
    const back = slotsFromGrid(gridFromSlots(slots));
    expect(back).toHaveLength(3);
    expect(back).toContainEqual({
      day_of_week: 1,
      slot_code: "P2",
      section_id: "A",
      subject_id: "eng",
      teacher_id: "t2",
      room_code: null,
    });
  });

  it("finds a teacher booked in two classes in the same period", () => {
    const grid = gridFromSlots(slots);
    expect(clashFor(grid, "A", 1, "P1", "t1")).toBe("B");
    expect(clashFor(grid, "A", 1, "P2", "t2")).toBeNull();
  });

  it("counts periods per subject in a class and per teacher in the school", () => {
    const grid = gridFromSlots(slots);
    expect(subjectLoad(grid, "A").get("math")).toBe(1);
    expect(teacherLoad(grid).get("t1")).toBe(2);
  });

  it("moves a class's periods of one subject to a new teacher only in that class", () => {
    const next = reassignTeacher(gridFromSlots(slots), "A", "math", "t9");
    expect(next.get(cellKey("A", 1, "P1"))?.teacherId).toBe("t9");
    expect(next.get(cellKey("B", 1, "P1"))?.teacherId).toBe("t1");
  });

  it("orders periods by start time and lists working days", () => {
    const shape = weekShape([
      { day_of_week: 2, slot_code: "P2", starts_at_local: "09:45", ends_at_local: "10:30" },
      { day_of_week: 1, slot_code: "P2", starts_at_local: "09:45", ends_at_local: "10:30" },
      { day_of_week: 1, slot_code: "P1", starts_at_local: "09:00", ends_at_local: "09:45" },
    ]);
    expect(shape.days).toEqual([1, 2]);
    expect(shape.codes.map((row) => row.code)).toEqual(["P1", "P2"]);
  });

  it("gives each subject a stable colour", () => {
    expect(subjectColour("MATH")).toBe(subjectColour("math"));
    expect(subjectColour("XYZ")).toBe(subjectColour("XYZ"));
  });
});
