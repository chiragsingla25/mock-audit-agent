export const API_DOWN_MESSAGE = "Can't reach the local API. Start it with `uv run mockaudit serve`.";

/** The browser couldn't connect to the local API at all. */
export class ApiUnreachableError extends Error {
  constructor() {
    super(API_DOWN_MESSAGE);
    this.name = "ApiUnreachableError";
  }
}

/** The API answered with an error status; `message` is its `detail`. */
export class ApiError extends Error {
  constructor(public status: number, message: string) {
    super(message);
    this.name = "ApiError";
  }
}
