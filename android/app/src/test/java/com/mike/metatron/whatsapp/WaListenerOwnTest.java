package com.mike.metatron.whatsapp;

import static org.junit.Assert.assertFalse;
import static org.junit.Assert.assertTrue;

import androidx.core.app.Person;

import org.junit.Test;

/**
 * The adapter's one decision: whether a messaging-style message is the user's own (never sent
 * live). androidx Person is plain Java, so this runs on the JVM. Names here are made up.
 */
public class WaListenerOwnTest {
    private static Person named(String name) {
        return new Person.Builder().setName(name).build();
    }

    private static Person keyed(String name, String key) {
        return new Person.Builder().setName(name).setKey(key).build();
    }

    @Test
    public void noPersonIsTheUsersOwn() {
        assertTrue(WaListener.isOwn(null, named("Self")));
        assertTrue(WaListener.isOwn(null, null));
    }

    @Test
    public void theStylesUserIsTheUsersOwn() {
        Person user = named("Self");
        assertTrue(WaListener.isOwn(user, user));
        assertTrue(WaListener.isOwn(named("Self"), named("Self")));
        assertTrue(WaListener.isOwn(keyed("Other", "k1"), keyed("Self", "k1")));
    }

    @Test
    public void anotherPersonIsReceived() {
        assertFalse(WaListener.isOwn(named("Contact A"), named("Self")));
        assertFalse(WaListener.isOwn(named("Contact A"), null));
        assertFalse(WaListener.isOwn(keyed("Self", "k2"), keyed("Self", "k1")));
        assertFalse(WaListener.isOwn(new Person.Builder().build(), named("Self")));
    }
}
