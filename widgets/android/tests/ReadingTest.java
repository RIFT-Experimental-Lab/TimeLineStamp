package lab.rift.timelinestamp.widget;

import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Paths;
import java.time.Instant;
import org.json.JSONObject;

/** JVM contract tests against the collector's published record, without Android stubs. */
public final class ReadingTest {
    private static int checks;
    private static void check(boolean condition) {
        checks++;
        if(!condition) throw new AssertionError("Check "+checks+" failed");
    }
    private static void rejected(JSONObject value) throws Exception {
        boolean rejected=false;
        try { Reading.parse(value.toString()); } catch(Exception expected) { rejected=true; }
        check(rejected);
    }
    public static void main(String[] args) throws Exception {
        String input=new String(Files.readAllBytes(Paths.get(args[0])),StandardCharsets.UTF_8);
        JSONObject original=new JSONObject(input);
        Reading actual=Reading.parse(input);
        check(actual!=null);
        check(actual.coefficient.equals(original.getJSONObject("current").getString("coefficient")));
        check(actual.digest.equals(Reading.parse(actual.compactJson()).digest));
        check(actual.coefficient.equals(Reading.parse(actual.compactJson()).coefficient));
        check(Reading.coefficient(new String(new char[64]).replace('\0','0')).equals("1.000000"));
        // This digest exercises rejection sampling rather than the usual modulo path.
        check(Reading.coefficient(new String(new char[64]).replace('\0','f')).equals(args[1]));
        JSONObject changed=new JSONObject(input);
        changed.getJSONObject("current").put("coefficient","1.999999"); rejected(changed);
        changed=new JSONObject(input);
        changed.getJSONObject("current").put("digest","invalid"); rejected(changed);
        changed=new JSONObject(input);
        changed.getJSONObject("current").put("created_at",actual.day+"T23:59:59Z"); rejected(changed);
        changed=new JSONObject(input);
        changed.put("published_at",actual.day+"T00:00:00Z"); rejected(changed);
        changed=new JSONObject(input);
        changed.getJSONObject("current").put("quality","unknown"); rejected(changed);
        changed=new JSONObject(input);
        changed.getJSONObject("current").put("quality","partial");
        check(Reading.parse(changed.toString()).coefficient.equals(actual.coefficient));
        changed.getJSONObject("current").put("quality","unavailable"); rejected(changed);
        changed.getJSONObject("current").put("coefficient",JSONObject.NULL);
        check(Reading.parse(changed.toString()).coefficient==null);
        changed=new JSONObject(input).put("current",JSONObject.NULL);
        changed.put("initial",original.getJSONObject("current"));
        check(Reading.parse(changed.toString())==null);
        changed=new JSONObject(input).put("format","unknown"); rejected(changed);
        JSONObject fixed=new JSONObject(actual.compactJson());
        fixed.getJSONObject("current").put("day","2026-10-25").put("created_at","2026-10-26T00:15:00Z");
        fixed.put("published_at","2026-10-26T00:16:00Z").put("v2_start_day_utc",JSONObject.NULL);
        Reading v1=Reading.parse(fixed.toString());
        check(!v1.delayed(Instant.parse("2026-10-27T03:15:00Z")));
        check(v1.delayed(Instant.parse("2026-10-27T03:15:01Z")));
        fixed.put("v2_start_day_utc","2026-10-26");
        Reading v2=Reading.parse(fixed.toString());
        check(!v2.delayed(Instant.parse("2026-10-29T03:15:00Z")));
        check(v2.delayed(Instant.parse("2026-10-29T03:15:01Z")));
        System.out.println(checks+" reading checks passed");
    }
}
