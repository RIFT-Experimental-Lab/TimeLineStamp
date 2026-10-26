package lab.rift.timelinestamp.widget;

import android.app.PendingIntent;
import android.appwidget.AppWidgetManager;
import android.content.ComponentName;
import android.content.Context;
import android.content.Intent;
import android.graphics.Color;
import android.net.Uri;
import android.widget.RemoteViews;
import java.time.Instant;
import java.time.ZoneOffset;
import java.time.format.DateTimeFormatter;
import java.util.Locale;

final class WidgetRenderer {
    static RemoteViews views(Context context) {
        RemoteViews views=new RemoteViews(context.getPackageName(),R.layout.stamp_widget);
        Reading record=Cache.reading(context);
        long checked=Cache.preferences(context).getLong("checked_at",0);
        boolean failed=Cache.preferences(context).getBoolean("failed",false);
        boolean online=WidgetUpdates.online(context);
        int[] digits={R.id.digit0,R.id.digit1,R.id.digit2,R.id.digit3,R.id.digit4,R.id.digit5,R.id.digit6};
        if(record!=null) {
            String number=record.coefficient==null?"———————":record.coefficient.replace(".","");
            for(int i=0;i<digits.length;i++) views.setTextViewText(digits[i],number.substring(i,i+1));
            views.setContentDescription(R.id.number,record.coefficient==null?context.getString(R.string.unavailable):record.coefficient);
            views.setTextViewText(R.id.utc_day,record.day);
            int quality=record.quality.equals("good")?R.string.good:record.quality.equals("partial")?R.string.partial:R.string.unavailable;
            views.setTextViewText(R.id.quality,context.getString(quality));
            views.setTextColor(R.id.quality,Color.parseColor(record.quality.equals("good")?"#AEC4B7":"#EFBB7E"));
        }
        String status;
        if(!online) status=context.getString(record==null?R.string.offline_empty:R.string.cached);
        else if(failed) status=context.getString(record==null?R.string.offline_empty:R.string.failed);
        else if(record!=null && record.delayed(Instant.now())) status=context.getString(R.string.delayed);
        else if(checked>0) status=context.getString(R.string.checked,DateTimeFormatter.ofPattern("HH:mm",Locale.ROOT)
            .withZone(ZoneOffset.UTC).format(Instant.ofEpochMilli(checked))+" UTC");
        else status=context.getString(R.string.not_checked);
        views.setTextViewText(R.id.sync_state,status);
        views.setTextViewText(R.id.refresh,"↻");
        Intent open=new Intent(Intent.ACTION_VIEW,Uri.parse(WidgetUpdates.SITE));
        PendingIntent website=PendingIntent.getActivity(context,1,open,PendingIntent.FLAG_IMMUTABLE|PendingIntent.FLAG_UPDATE_CURRENT);
        views.setOnClickPendingIntent(R.id.widget_root,website);
        PendingIntent refresh=PendingIntent.getBroadcast(context,2,new Intent(context,RefreshReceiver.class),PendingIntent.FLAG_IMMUTABLE|PendingIntent.FLAG_UPDATE_CURRENT);
        views.setOnClickPendingIntent(R.id.refresh,refresh);
        return views;
    }
    static void renderAll(Context context) {
        AppWidgetManager manager=AppWidgetManager.getInstance(context);
        for(int id:manager.getAppWidgetIds(new ComponentName(context,StampWidget.class))) manager.updateAppWidget(id,views(context));
    }
}
