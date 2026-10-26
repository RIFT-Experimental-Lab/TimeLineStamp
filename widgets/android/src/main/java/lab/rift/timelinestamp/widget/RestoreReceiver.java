package lab.rift.timelinestamp.widget;
import android.content.BroadcastReceiver;
import android.content.Context;
import android.content.Intent;
public final class RestoreReceiver extends BroadcastReceiver {
    @Override public void onReceive(Context context,Intent intent) {
        WidgetRenderer.renderAll(context); WidgetUpdates.periodic(context);
        if(WidgetUpdates.hasWidgets(context)) WidgetUpdates.request(context);
    }
}
