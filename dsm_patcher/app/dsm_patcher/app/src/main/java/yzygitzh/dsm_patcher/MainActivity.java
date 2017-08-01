package yzygitzh.dsm_patcher;

import android.support.design.widget.Snackbar;
import android.support.v7.app.AppCompatActivity;
import android.os.Bundle;
import android.view.View;

public class MainActivity extends AppCompatActivity {

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        setContentView(R.layout.activity_main);

        final View refreshButton = findViewById(R.id.refresh_button);

        refreshButton.setOnClickListener(new View.OnClickListener() {
            public void onClick(View v) {
                if (DSMRules.initDSMRules() && DSMPatcher.hookDSMRulePackages()) {
                    Snackbar.make(v, R.string.dsm_success_msg, Snackbar.LENGTH_SHORT).show();
                } else {
                    Snackbar.make(v, R.string.dsm_fail_msg, Snackbar.LENGTH_SHORT).show();
                }
            }
        });
    }
}
