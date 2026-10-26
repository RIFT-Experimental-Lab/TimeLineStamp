package lab.rift.timelinestamp.widget;

import android.app.job.JobInfo;
import android.app.job.JobScheduler;
import android.appwidget.AppWidgetManager;
import android.content.ComponentName;
import android.content.Context;
import android.net.ConnectivityManager;
import android.net.NetworkCapabilities;

final class WidgetUpdates {
    static final int PERIODIC=4101, MANUAL=4102;
    static final String SITE="https://rift-experimental-lab.github.io/TimeLineStamp/";
    static final String STATUS=SITE+"data/status.json";
    static boolean hasWidgets(Context context) {
        return AppWidgetManager.getInstance(context).getAppWidgetIds(new ComponentName(context,StampWidget.class)).length>0;
    }
    static void periodic(Context context) {
        JobScheduler scheduler=(JobScheduler)context.getSystemService(Context.JOB_SCHEDULER_SERVICE);
        if(!hasWidgets(context)) { scheduler.cancel(PERIODIC); return; }
        if(scheduler.getPendingJob(PERIODIC)==null) scheduler.schedule(new JobInfo.Builder(PERIODIC,new ComponentName(context,RefreshJob.class))
            .setRequiredNetworkType(JobInfo.NETWORK_TYPE_ANY).setPeriodic(30*60*1000L).setPersisted(true).build());
    }
    static void request(Context context) {
        WidgetRenderer.renderAll(context);
        long last=Cache.preferences(context).getLong("attempted_at",0);
        if(System.currentTimeMillis()-last<30000) return;
        JobScheduler scheduler=(JobScheduler)context.getSystemService(Context.JOB_SCHEDULER_SERVICE);
        scheduler.schedule(new JobInfo.Builder(MANUAL,new ComponentName(context,RefreshJob.class))
            .setRequiredNetworkType(JobInfo.NETWORK_TYPE_ANY).build());
    }
    static boolean online(Context context) {
        ConnectivityManager manager=(ConnectivityManager)context.getSystemService(Context.CONNECTIVITY_SERVICE);
        NetworkCapabilities caps=manager.getNetworkCapabilities(manager.getActiveNetwork());
        return caps!=null && caps.hasCapability(NetworkCapabilities.NET_CAPABILITY_INTERNET)
            && caps.hasCapability(NetworkCapabilities.NET_CAPABILITY_VALIDATED);
    }
}
