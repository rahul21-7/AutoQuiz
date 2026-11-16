// AutoQuiz AI Platform - UCP Estimation Calculator
// Transcribed directly from Software Engineering Report (Pages 75-78)
#include <iostream>
#include <iomanip>
#include <string>
#include <unordered_map>

using namespace std;

// Classifies use cases based on number of transactions
string classifyUseCase(int transactions) {
    if (transactions <= 3)
        return "Simple";
    else if (transactions <= 7)
        return "Average";
    else
        return "Complex";
}

int main() {
    cout << "=========================================================\n";
    cout << " AUTOQUIZ AI PLATFORM - UCP ESTIMATION CALCULATOR\n";
    cout << "=========================================================\n";

    // Unadjusted Use Case Weight (UUCW)
    int simpleUC = 8;    // 8 Simple Use Cases (Weight 5) = 40
    int averageUC = 7;   // 7 Average Use Cases (Weight 10) = 70
    int complexUC = 5;   // 5 Complex Use Cases (Weight 15) = 75
    int uucw = (simpleUC * 5) + (averageUC * 10) + (complexUC * 15); // 185

    // Unadjusted Actor Weight (UAW)
    int simpleActor = 4; // 4 Simple Actors (Weight 1) = 4
    int averageActor = 1;// 1 Average Actor (Weight 2) = 2
    int complexActor = 1;// 1 Complex Actor (Weight 3) = 3
    int uaw = (simpleActor * 1) + (averageActor * 2) + (complexActor * 3); // 9

    // Technical Complexity Factors (TCF)
    unordered_map<string, float> tcfWeights = {
        {"Distributed system", 2.0},
        {"Response time/performance objectives", 1.0},
        {"End-user efficiency", 1.0},
        {"Internal processing complexity", 1.0},
        {"Code reusability", 1.0},
        {"Easy to install", 0.5},
        {"Easy to use", 0.5},
        {"Portability to other platforms", 2.0},
        {"System maintenance", 1.0},
        {"Concurrent/parallel processing", 1.0},
        {"Security features", 1.0},
        {"Access for third parties", 1.0},
        {"End user training", 1.0}
    };
    
    // Ratings from Table 4.1 in report
    unordered_map<string, float> tcfRatings = {
        {"Distributed system", 1.0},
        {"Response time/performance objectives", 4.0},
        {"End-user efficiency", 4.0},
        {"Internal processing complexity", 5.0},
        {"Code reusability", 3.0},
        {"Easy to install", 3.0},
        {"Easy to use", 4.0},
        {"Portability to other platforms", 3.0},
        {"System maintenance", 3.0},
        {"Concurrent/parallel processing", 3.0},
        {"Security features", 5.0},
        {"Access for third parties", 1.0},
        {"End user training", 2.0}
    };

    float tfSum = 0;
    for (const auto& pair : tcfWeights) {
        tfSum += pair.second * tcfRatings[pair.first];
    }
    float tcf = 0.6f + (tfSum / 100.0f); // 1.01500

    // Environmental Complexity Factors (ECF)
    unordered_map<string, float> ecfWeights = {
        {"Familiar with development process used", 1.5},
        {"Application experience", 0.5},
        {"Object-oriented experience of team", 1.0},
        {"Lead analyst capability", 0.5},
        {"Motivation of the team", 1.0},
        {"Stability of Requirements", 2.0},
        {"Part-time staff", -1.0},
        {"Difficult programming language", -1.0}
    };

    unordered_map<string, float> ecfRatings = {
        {"Familiar with development process used", 4.0},
        {"Application experience", 3.0},
        {"Object-oriented experience of team", 4.0},
        {"Lead analyst capability", 3.0},
        {"Motivation of the team", 5.0},
        {"Stability of Requirements", 4.0},
        {"Part-time staff", 2.0},
        {"Difficult programming language", 1.0}
    };

    float efSum = 0;
    for (const auto& pair : ecfWeights) {
        efSum += pair.second * ecfRatings[pair.first];
    }
    float ecf = 1.4f + (-0.03f * efSum); // 0.71000

    float pf = 8.0f; // Productivity Factor: 8 hours per UCP
    float uucp = (float)(uucw + uaw);
    float ucp = uucp * tcf * ecf;
    float effort = ucp * pf;

    cout << fixed << setprecision(5);
    cout << "\n=========================================================\n";
    cout << " UCP ESTIMATION FINAL SUMMARY \n";
    cout << "=========================================================\n";
    cout << "UUCW (Unadjusted Use Case Weight) : " << uucw << endl;
    cout << "UAW (Unadjusted Actor Weight) : " << uaw << endl;
    cout << "UUCP (Unadjusted Use Case Points) : " << (int)uucp << endl;
    cout << "TCF (Technical Complexity Factor) : " << tcf << endl;
    cout << "ECF (Environmental Complexity Factor): " << ecf << endl;
    cout << "UCP (Adjusted Use Case Points) : " << ucp << endl;
    cout << "Estimated Total Effort : " << effort << " person-hours" << endl;

    return 0;
}

