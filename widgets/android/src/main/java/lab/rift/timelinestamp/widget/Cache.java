package lab.rift.timelinestamp.widget;

import android.content.Context;
import android.content.SharedPreferences;

final class Cache {
    static SharedPreferences preferences(Context context) { return context.getSharedPreferences("sealed-record",Context.MODE_PRIVATE); }
    static Reading reading(Context context) {
        try { return Reading.parse(preferences(context).getString("record","")); }
        catch(Exception ignored) { return null; }
    }
    static void success(Context context, Reading reading) throws Exception {
        SharedPreferences.Editor editor=preferences(context).edit().putLong("checked_at",System.currentTimeMillis()).putBoolean("failed",false);
        if(reading!=null) editor.putString("record",reading.compactJson());
        editor.apply();
    }
    static void failure(Context context) { preferences(context).edit().putBoolean("failed",true).apply(); }
}
