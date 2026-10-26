package lab.rift.timelinestamp.widget;

import android.appwidget.AppWidgetManager;
import android.appwidget.AppWidgetProvider;
import android.content.Context;
import android.os.Bundle;

public final class StampWidget extends AppWidgetProvider {
    @Override public void onUpdate(Context context,AppWidgetManager manager,int[] ids) {
        WidgetRenderer.renderAll(context); WidgetUpdates.periodic(context); WidgetUpdates.request(context);
    }
    @Override public void onEnabled(Context context) { WidgetUpdates.periodic(context); }
    @Override public void onDisabled(Context context) { WidgetUpdates.periodic(context); }
    @Override public void onAppWidgetOptionsChanged(Context context,AppWidgetManager manager,int id,Bundle options) {
        manager.updateAppWidget(id,WidgetRenderer.views(context));
    }
}
