import type { Ref } from "vue";

/**
 * Creates a snackbar visibility handler that clears its message after dismissal.
 *
 * Vuetify emits `false` when the snackbar closes; retaining the message until
 * then lets its close transition render the message correctly.
 */
export function createSnackbarDismissHandler(
  message: Ref<string>,
): (visible: boolean) => void {
  return (visible: boolean): void => {
    if (visible) {
      return;
    }

    message.value = "";
  };
}
