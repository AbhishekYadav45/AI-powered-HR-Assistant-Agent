# report_generator.py - Dynamic report generator
import matplotlib.pyplot as plt
import pandas as pd
import numpy as np

def generate_dynamic_report(df, report_path="report.png"):
    """
    Dynamically generates visualization based on available columns.
    Falls back to CSV if visualization is not suitable.
    """
    if df.empty:
        return None

    if df.shape[1] == 1:
        report_path = "report.csv"
        df.to_csv(report_path, index=False)
        return report_path

    numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()

    if df.shape[1] == 2:
        col1, col2 = df.columns
        plt.figure(figsize=(8, 5))
        if df[col1].dtype == "object" or df[col2].dtype == "object":
            plt.bar(df[col1], df[col2], color="skyblue")
            plt.xlabel(col1)
            plt.ylabel(col2)
            plt.title(f"{col2} by {col1}")
            plt.xticks(rotation=30)
        else:
            plt.scatter(df[col1], df[col2], color="purple")
            plt.xlabel(col1)
            plt.ylabel(col2)
            plt.title(f"{col1} vs {col2}")
        plt.tight_layout()
        plt.savefig(report_path)
        plt.close()
        return report_path

    if len(numeric_cols) > 1:
        corr = df[numeric_cols].corr()
        plt.figure(figsize=(7, 5))
        plt.imshow(corr, cmap="coolwarm", interpolation="nearest")
        plt.colorbar(label="Correlation")
        plt.xticks(range(len(corr)), corr.columns, rotation=30)
        plt.yticks(range(len(corr)), corr.columns)
        plt.title("Correlation Heatmap")
        plt.tight_layout()
        plt.savefig(report_path)
        plt.close()
        return report_path

    report_path = "report.csv"
    df.to_csv(report_path, index=False)
    return report_path
