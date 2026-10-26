package lab.rift.timelinestamp.widget;

import android.app.job.JobParameters;
import android.app.job.JobService;
import java.io.ByteArrayOutputStream;
import java.io.InputStream;
import java.net.HttpURLConnection;
import java.net.URL;
import java.nio.charset.StandardCharsets;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import java.util.concurrent.Future;
import java.util.concurrent.atomic.AtomicReference;
import java.util.concurrent.ConcurrentHashMap;

public final class RefreshJob extends JobService {
    private static final AtomicReference<Run> ACTIVE=new AtomicReference<>();
    private final ExecutorService executor=Executors.newSingleThreadExecutor();
    private final ConcurrentHashMap<Integer,Run> tasks=new ConcurrentHashMap<>();
    private static final class Run {
        volatile boolean stopped;
        volatile HttpURLConnection connection;
        volatile Future<?> task;
    }

    @Override public boolean onStartJob(JobParameters parameters) {
        Run run=new Run();
        if(!ACTIVE.compareAndSet(null,run)) return false;
        tasks.put(parameters.getJobId(),run);
        run.task=executor.submit(()-> {
            Cache.preferences(this).edit().putLong("attempted_at",System.currentTimeMillis()).apply();
            try {
                HttpURLConnection connection=(HttpURLConnection)new URL(WidgetUpdates.STATUS+"?t="+System.currentTimeMillis()).openConnection();
                run.connection=connection;
                connection.setConnectTimeout(12000); connection.setReadTimeout(15000);
                connection.setInstanceFollowRedirects(false);
                connection.setRequestProperty("Accept","application/json");
                connection.setRequestProperty("Cache-Control","no-cache");
                connection.setRequestProperty("User-Agent","TimeLineStamp-AndroidWidget/0.2");
                if(connection.getResponseCode()!=200) throw new IllegalArgumentException("Status HTTP failure");
                ByteArrayOutputStream data=new ByteArrayOutputStream();
                try(InputStream input=connection.getInputStream()) {
                    byte[] buffer=new byte[8192]; int count;
                    while((count=input.read(buffer))!=-1) {
                        if(data.size()+count>4*1024*1024) throw new IllegalArgumentException("Status exceeds 4 MiB");
                        data.write(buffer,0,count);
                        if(Thread.currentThread().isInterrupted()) return;
                    }
                }
                Reading reading=Reading.parse(new String(data.toByteArray(),StandardCharsets.UTF_8));
                Reading previous=Cache.reading(this);
                if(previous!=null && (reading==null || reading.day.compareTo(previous.day)<0))
                    throw new IllegalArgumentException("Response is older than the saved record");
                if(!run.stopped) Cache.success(this,reading);
            } catch(Exception ignored) {
                if(!run.stopped) Cache.failure(this);
            } finally {
                if(run.connection!=null) run.connection.disconnect();
                ACTIVE.compareAndSet(run,null);
                tasks.remove(parameters.getJobId(),run);
                if(!run.stopped) { WidgetRenderer.renderAll(this); jobFinished(parameters,false); }
            }
        });
        return true;
    }
    @Override public boolean onStopJob(JobParameters parameters) {
        Run run=tasks.remove(parameters.getJobId());
        if(run==null) return false;
        stop(run);
        return true;
    }
    private void stop(Run run) {
        run.stopped=true;
        if(run.connection!=null) run.connection.disconnect();
        if(run.task!=null) run.task.cancel(true);
        ACTIVE.compareAndSet(run,null);
    }
    @Override public void onDestroy() {
        for(Run run:tasks.values()) stop(run);
        tasks.clear(); executor.shutdownNow(); super.onDestroy();
    }
}
