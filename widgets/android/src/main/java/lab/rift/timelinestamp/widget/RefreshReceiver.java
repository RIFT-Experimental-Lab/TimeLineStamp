package lab.rift.timelinestamp.widget;
import android.content.BroadcastReceiver;
import android.content.Context;
import android.content.Intent;
public final class RefreshReceiver extends BroadcastReceiver {
    @Override public void onReceive(Context context,Intent intent) { WidgetUpdates.request(context); }
}
