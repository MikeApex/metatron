package com.mike.metatron.whatsapp;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertFalse;
import static org.junit.Assert.assertTrue;

import java.util.Map;

import org.junit.Test;

/** The client's address guard and reply reading (plan § 3.8, § 3.7). */
public class DeviceClientTest {
    private static final String PLANTED = "planted-value-Zq81";

    @Test
    public void onlyHttpsAddressesAreAccepted() {
        assertTrue(DeviceClient.isHttps("https://metatron.example.test"));
        assertTrue(DeviceClient.isHttps("https://10.0.0.2:8443/"));
        assertTrue("the scheme is case-insensitive", DeviceClient.isHttps("HTTPS://metatron.example.test"));
        assertTrue(DeviceClient.isHttps("Https://metatron.example.test"));
        assertFalse(DeviceClient.isHttps("http://metatron.example.test"));
        assertFalse(DeviceClient.isHttps("HTTP://metatron.example.test"));
        assertFalse(DeviceClient.isHttps("http://localhost:8000"));
        assertFalse(DeviceClient.isHttps(""));
        assertFalse(DeviceClient.isHttps(null));
        assertFalse(DeviceClient.isHttps("https://"));
        assertFalse(DeviceClient.isHttps("https:/metatron.example.test"));
        assertFalse(DeviceClient.isHttps(" https://metatron.example.test"));
        assertFalse(DeviceClient.isHttps("ftp://metatron.example.test"));
        assertFalse(DeviceClient.isHttps("metatron.example.test"));
    }

    @Test
    public void refusedAddressMakesNoRequest() {
        DeviceApi.Result r = DeviceClient.send("http://metatron.example.test", "d1.tok", "GET", "/device/whatsapp/cursor", null, 1000);
        assertEquals(DeviceApi.NOT_HTTPS, r.status);
        assertEquals("not_https", r.detail);
        assertEquals("", r.body);
    }

    @Test
    public void networkFailureCarriesTheClassNameNeverTheMessage() {
        DeviceApi.Result r = DeviceClient.networkFailure(new java.net.SocketTimeoutException("read timed out " + PLANTED));
        assertEquals(DeviceApi.NETWORK, r.status);
        assertEquals("SocketTimeoutException", r.detail);
        assertFalse(r.detail.contains(PLANTED));
        assertFalse(r.body.contains(PLANTED));
    }

    @Test
    public void detailIsTheReplysDetailString() {
        assertEquals("consented_off", DeviceClient.detailOf("{\"detail\":\"consented_off\"}"));
        assertEquals("channel_off", DeviceClient.detailOf("{\"detail\": \"channel_off\", \"x\": 1}"));
    }

    @Test
    public void noDetailIsEmpty() {
        assertEquals("", DeviceClient.detailOf(""));
        assertEquals("", DeviceClient.detailOf(null));
        assertEquals("", DeviceClient.detailOf("{\"cursor\":null}"));
        assertEquals("", DeviceClient.detailOf("<html>" + PLANTED + "</html>"));
        assertEquals("", DeviceClient.detailOf("[\"detail\"]"));
        // FastAPI's validation errors put a list in detail: not a string, so no detail.
        assertEquals("", DeviceClient.detailOf("{\"detail\":[{\"msg\":\"" + PLANTED + "\"}]}"));
    }

    @Test
    public void jsonStringRoundTripsThroughTheReader() throws Exception {
        String label = "Phone \"model\" \\ x\n\t\u0001 é";
        Object v = Json.parse("{\"label\":" + DeviceClient.jsonString(label) + "}");
        assertEquals(label, ((Map<?, ?>) v).get("label"));
    }
}
