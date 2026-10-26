package lab.rift.timelinestamp.widget;

import org.json.JSONObject;
import java.math.BigInteger;
import java.security.MessageDigest;
import java.time.Instant;
import java.time.LocalDate;
import java.time.ZoneOffset;
import java.util.Locale;

/** The published daily record; no initial or in-progress readings are substituted. */
public final class Reading {
    public final String day, digest, coefficient, quality, publishedAt, createdAt, v2Start;

    private Reading(String day, String digest, String coefficient, String quality,
                    String publishedAt, String createdAt, String v2Start) {
        this.day=day; this.digest=digest; this.coefficient=coefficient; this.quality=quality;
        this.publishedAt=publishedAt; this.createdAt=createdAt; this.v2Start=v2Start;
    }

    public static Reading parse(String json) throws Exception {
        JSONObject root=new JSONObject(json);
        if (!"timelinestamp-status-v1".equals(root.getString("format"))) throw new IllegalArgumentException("Unknown status format");
        Instant published=Instant.parse(root.getString("published_at"));
        JSONObject record=root.optJSONObject("current");
        if (record==null) return null;
        String day=record.getString("day"), digest=record.getString("digest"), quality=record.getString("quality");
        LocalDate date=LocalDate.parse(day);
        if (!date.toString().equals(day) || !digest.matches("[a-f0-9]{64}")) throw new IllegalArgumentException("Invalid record");
        Instant created=Instant.parse(record.getString("created_at"));
        if (created.isBefore(date.plusDays(1).atStartOfDay(ZoneOffset.UTC).toInstant()) || published.isBefore(created))
            throw new IllegalArgumentException("Unsealed date or invalid publication time");
        if (!quality.equals("good") && !quality.equals("partial") && !quality.equals("unavailable"))
            throw new IllegalArgumentException("Unknown quality");
        String number=record.isNull("coefficient") ? null : record.getString("coefficient");
        if (quality.equals("unavailable")) {
            if (number!=null) throw new IllegalArgumentException("Unavailable record has a number");
        } else if (number==null || !number.matches("1\\.[0-9]{6}") || !number.equals(coefficient(digest))) {
            throw new IllegalArgumentException("Number does not match the published hash");
        }
        String v2=root.isNull("v2_start_day_utc") || !root.has("v2_start_day_utc") ? null : root.getString("v2_start_day_utc");
        if (v2!=null) LocalDate.parse(v2);
        return new Reading(day,digest,number,quality,published.toString(),created.toString(),v2);
    }

    public static String coefficient(String digest) throws Exception {
        byte[] bytes=new byte[32];
        for(int i=0;i<32;i++) bytes[i]=(byte)Integer.parseInt(digest.substring(i*2,i*2+2),16);
        BigInteger modulus=BigInteger.valueOf(1000000), range=BigInteger.ONE.shiftLeft(256);
        BigInteger limit=range.subtract(range.mod(modulus));
        BigInteger candidate=new BigInteger(1,bytes);
        while(candidate.compareTo(limit)>=0) {
            bytes=MessageDigest.getInstance("SHA-256").digest(bytes);
            candidate=new BigInteger(1,bytes);
        }
        return String.format(Locale.ROOT,"1.%06d",candidate.mod(modulus).intValue());
    }

    public boolean delayed(Instant now) {
        LocalDate latest=LocalDate.parse(day), next=latest.plusDays(1);
        boolean v2=v2Start!=null && !next.isBefore(LocalDate.parse(v2Start));
        Instant due=latest.plusDays(v2?4:2).atStartOfDay(ZoneOffset.UTC).plusMinutes(15).plusHours(3).toInstant();
        return now.isAfter(due);
    }

    public String compactJson() throws Exception {
        JSONObject record=new JSONObject().put("day",day).put("digest",digest).put("quality",quality)
            .put("coefficient",coefficient==null?JSONObject.NULL:coefficient).put("created_at",createdAt);
        return new JSONObject().put("format","timelinestamp-status-v1").put("published_at",publishedAt)
            .put("v2_start_day_utc",v2Start==null?JSONObject.NULL:v2Start).put("current",record).toString();
    }
}
