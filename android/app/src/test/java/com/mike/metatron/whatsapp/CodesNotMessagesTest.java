package com.mike.metatron.whatsapp;

import static org.junit.Assert.assertTrue;
import static org.junit.Assert.fail;

import java.io.File;
import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

import org.junit.Test;

/**
 * Codes, never messages (plan § 3.7): no exception's message may reach a notification, a
 * screen, a post or a log. This reads the shipped WhatsApp sources and fails on any
 * {@code getMessage()} / {@code getLocalizedMessage()} outside the named allowlist.
 *
 * The working directory of a unit test is the module dir (android/app).
 */
public class CodesNotMessagesTest {
    private static final File WHATSAPP = new File("src/main/java/com/mike/metatron/whatsapp");
    private static final File APP = new File("src/main/java/com/mike/metatron/MetatronApp.java");

    /**
     * Reader files that already use getMessage(), each with why it cannot reach a user:
     * - IncrementReader.java: folds a Json.Malformed's message — a position ("… at character
     *   N"), never content — into a BackupException's detail. A BackupException's own message
     *   is itself never shown (§ 3.7): callers show error.userText and report error.code.
     * The count is exact, so a new use in an allowlisted file fails too.
     */
    private static final Map<String, Integer> ALLOWED = new HashMap<>();
    static {
        ALLOWED.put("IncrementReader.java", 1);
    }

    @Test
    public void noExceptionMessageInPhase2Sources() throws IOException {
        assertTrue("run from the module dir: " + WHATSAPP.getAbsolutePath(), WHATSAPP.isDirectory());
        List<File> files = new ArrayList<>();
        collect(WHATSAPP, files);
        files.add(APP);
        List<String> found = new ArrayList<>();
        int read = 0;
        for (File f : files) {
            if (!f.isFile()) continue;
            read++;
            List<String> lines = Files.readAllLines(f.toPath(), StandardCharsets.UTF_8);
            List<String> here = new ArrayList<>();
            for (int i = 0; i < lines.size(); i++) {
                String l = lines.get(i);
                if (l.contains("getMessage(") || l.contains("getLocalizedMessage(")) {
                    here.add(f.getName() + ":" + (i + 1));
                }
            }
            Integer allowed = ALLOWED.get(f.getName());
            if (allowed == null || here.size() != allowed) found.addAll(here);
        }
        assertTrue("expected to read the WhatsApp sources, read " + read, read > 10);
        if (!found.isEmpty()) {
            fail("an exception's message could reach a screen, notice, post or log — report "
                    + "error.code / show error.userText / the exception's simple class name instead: " + found);
        }
    }

    @Test
    public void allowlistedFilesExist() {
        for (String name : ALLOWED.keySet()) {
            assertTrue("stale allowlist entry " + name, new File(WHATSAPP, name).isFile());
        }
    }

    private static void collect(File dir, List<File> out) {
        File[] kids = dir.listFiles();
        if (kids == null) return;
        for (File k : kids) {
            if (k.isDirectory()) collect(k, out);
            else if (k.getName().endsWith(".java")) out.add(k);
        }
    }
}
