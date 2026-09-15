export type ClassAllocation = {
  level: number;
  class_entry_id?: number;
  class_name: string;
};

export function sameClass(left: ClassAllocation, right: ClassAllocation): boolean {
  if (left.class_entry_id || right.class_entry_id) {
    return left.class_entry_id === right.class_entry_id;
  }
  return (
    Boolean(left.class_name.trim()) &&
    left.class_name.trim().toLocaleLowerCase() ===
      right.class_name.trim().toLocaleLowerCase()
  );
}

export function classLevelAt(
  allocations: ClassAllocation[],
  row: ClassAllocation,
): number {
  return allocations.filter(
    (candidate) => candidate.level <= row.level && sameClass(candidate, row),
  ).length;
}
