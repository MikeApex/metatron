package com.mike.metatron.whatsapp;

/**
 * Every call the phone makes to the VM's /device/* routes (plan § 3.8). {@link DeviceClient} is
 * the real one; tests supply a fake. Every reply should pass through {@link Gate#observe}.
 *
 * A Result never carries an exception's message: on a network failure {@code detail} is the
 * exception's simple class name and nothing more (§ 3.7).
 */
public interface DeviceApi {
    /** No reply: the request failed on the way. {@code detail} = the exception's simple class name. */
    int NETWORK = -1;
    /** The server address is not https://. No request was made; {@code detail} = "not_https". */
    int NOT_HTTPS = -2;
    /** No device token is stored. No request was made; {@code detail} = "unpaired". */
    int UNPAIRED = -3;

    Result get(String path);

    Result post(String path, String jsonBody, int readTimeoutMs);

    final class Result {
        /** The HTTP status, or one of the negative codes above. */
        public final int status;
        /** The raw response text ("" when there was none). Parse with {@link Json}. */
        public final String body;
        /** The response's JSON "detail" string when there is one, a negative code's reason, else "". */
        public final String detail;

        public Result(int status, String body, String detail) {
            this.status = status;
            this.body = body == null ? "" : body;
            this.detail = detail == null ? "" : detail;
        }
    }
}
