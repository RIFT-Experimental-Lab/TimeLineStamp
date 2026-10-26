package lab.rift.timelinestamp.widget;

import android.app.Activity;
import android.appwidget.AppWidgetManager;
import android.content.ComponentName;
import android.content.Intent;
import android.content.SharedPreferences;
import android.graphics.Color;
import android.graphics.Typeface;
import android.graphics.drawable.GradientDrawable;
import android.net.Uri;
import android.os.Bundle;
import android.view.Gravity;
import android.view.View;
import android.widget.Button;
import android.widget.FrameLayout;
import android.widget.LinearLayout;
import android.widget.ScrollView;
import android.widget.TextView;
import android.widget.Toast;

public final class MainActivity extends Activity implements SharedPreferences.OnSharedPreferenceChangeListener {
    private FrameLayout preview;
    private static final int TEXT=Color.rgb(219,226,222), MUTED=Color.rgb(150,166,163), AMBER=Color.rgb(239,187,126);
    private int dp(int value) { return Math.round(value*getResources().getDisplayMetrics().density); }
    private TextView label(String value,int size,int color,boolean mono) {
        TextView view=new TextView(this); view.setText(value); view.setTextSize(size); view.setTextColor(color);
        view.setTypeface(mono?Typeface.MONOSPACE:Typeface.create("sans-serif",Typeface.NORMAL));
        view.setIncludeFontPadding(false); return view;
    }
    private void space(LinearLayout parent,int height) { parent.addView(new View(this),new LinearLayout.LayoutParams(1,dp(height))); }
    private void rule(LinearLayout parent) { View view=new View(this); view.setBackgroundColor(Color.rgb(49,64,67)); parent.addView(view,new LinearLayout.LayoutParams(-1,dp(1))); }
    private GradientDrawable panel(int fill,int border) {
        GradientDrawable drawable=new GradientDrawable(); drawable.setColor(fill); drawable.setStroke(dp(1),border); return drawable;
    }
    private Button button(String title,LinearLayout parent,boolean primary) {
        Button button=new Button(this); button.setText(title); button.setAllCaps(false); button.setTextSize(11);
        button.setTypeface(Typeface.MONOSPACE); button.setLetterSpacing(0.04f);
        button.setTextColor(primary?AMBER:MUTED); button.setGravity(Gravity.CENTER_VERTICAL|Gravity.LEFT);
        button.setPadding(dp(14),0,dp(14),0); button.setStateListAnimator(null); button.setMinHeight(0); button.setMinimumHeight(0);
        button.setBackground(panel(primary?Color.rgb(34,32,26):Color.rgb(13,21,23),primary?Color.rgb(166,132,91):Color.rgb(49,64,67)));
        LinearLayout.LayoutParams params=new LinearLayout.LayoutParams(-1,dp(primary?48:42)); params.bottomMargin=dp(8);
        parent.addView(button,params); return button;
    }
    @Override public void onCreate(Bundle saved) {
        super.onCreate(saved);
        getWindow().setStatusBarColor(Color.rgb(9,14,16)); getWindow().setNavigationBarColor(Color.rgb(9,14,16));
        ScrollView scroll=new ScrollView(this); scroll.setFillViewport(true); scroll.setBackgroundColor(Color.rgb(9,14,16));
        scroll.setOnApplyWindowInsetsListener((view,insets)-> {
            view.setPadding(insets.getSystemWindowInsetLeft(),insets.getSystemWindowInsetTop(),insets.getSystemWindowInsetRight(),insets.getSystemWindowInsetBottom());
            return insets.consumeSystemWindowInsets();
        });
        LinearLayout body=new LinearLayout(this); body.setOrientation(LinearLayout.VERTICAL); body.setPadding(dp(22),dp(20),dp(22),dp(24));
        scroll.addView(body); setContentView(scroll);
        LinearLayout masthead=new LinearLayout(this); masthead.setGravity(Gravity.CENTER_VERTICAL);
        TextView mark=label("T.",19,AMBER,true); mark.setGravity(Gravity.CENTER); mark.setBackground(panel(Color.TRANSPARENT,Color.rgb(83,103,91)));
        masthead.addView(mark,new LinearLayout.LayoutParams(dp(34),dp(34)));
        LinearLayout identity=new LinearLayout(this); identity.setOrientation(LinearLayout.VERTICAL); identity.setPadding(dp(11),0,0,0);
        TextView name=label("TIMELINESTAMP",11,TEXT,false); name.setLetterSpacing(0.15f); name.setTypeface(Typeface.create("sans-serif-medium",Typeface.NORMAL));
        identity.addView(name); space(identity,4); identity.addView(label("R.I.F.T. / EXPERIMENT 001",7,MUTED,true));
        masthead.addView(identity,new LinearLayout.LayoutParams(0,-2,1)); masthead.addView(label("TS-01\nUTC",8,MUTED,true));
        body.addView(masthead); space(body,18); rule(body); space(body,25);
        TextView title=label("A fingerprint\nof the timeline.",29,TEXT,false); title.setLetterSpacing(-0.025f); body.addView(title);
        space(body,12); TextView introduction=label("One sealed record. One UTC day.\nKeep the number in mind.",12,MUTED,false); introduction.setLineSpacing(dp(3),1); body.addView(introduction);
        space(body,25); body.addView(label("01 / HOME SCREEN DISPLAY",8,MUTED,true)); space(body,10);
        preview=new FrameLayout(this); body.addView(preview,new LinearLayout.LayoutParams(-1,dp(172)));
        space(body,10); body.addView(label("PUBLIC RECORD / READ ONLY",7,MUTED,true)); space(body,22);
        button(getString(R.string.add_widget),body,true).setOnClickListener(view->{
            AppWidgetManager manager=AppWidgetManager.getInstance(this);
            if(manager.isRequestPinAppWidgetSupported()) manager.requestPinAppWidget(new ComponentName(this,StampWidget.class),null,null);
            else Toast.makeText(this,R.string.pin_unsupported,Toast.LENGTH_LONG).show();
        });
        button("REFRESH RECORD  ↻",body,false).setOnClickListener(view->{WidgetUpdates.request(this); Toast.makeText(this,R.string.refresh_requested,Toast.LENGTH_SHORT).show();});
        button(getString(R.string.open_site),body,false).setOnClickListener(view->startActivity(new Intent(Intent.ACTION_VIEW,Uri.parse(WidgetUpdates.SITE))));
        space(body,17); rule(body); space(body,18);
        body.addView(label("02 / OPERATOR NOTES",8,MUTED,true)); space(body,10);
        TextView instructions=label(getString(R.string.instructions),12,TEXT,false); instructions.setLineSpacing(dp(3),1); body.addView(instructions);
        space(body,14); TextView note=label(getString(R.string.background_note),10,MUTED,false); note.setLineSpacing(dp(3),1); body.addView(note);
        space(body,20); body.addView(label("RIFT / TEMPORAL OBSERVATION",7,MUTED,true));
        WidgetUpdates.periodic(this); WidgetUpdates.request(this);
    }
    private void updatePreview() { if(preview!=null) { preview.removeAllViews(); preview.addView(WidgetRenderer.views(this).apply(this,preview)); } }
    @Override public void onResume() { super.onResume(); Cache.preferences(this).registerOnSharedPreferenceChangeListener(this); updatePreview(); WidgetRenderer.renderAll(this); }
    @Override public void onPause() { Cache.preferences(this).unregisterOnSharedPreferenceChangeListener(this); super.onPause(); }
    @Override public void onSharedPreferenceChanged(SharedPreferences preferences,String key) { runOnUiThread(this::updatePreview); }
}
