#include "test_precomp.hpp"
#include <time.h>

using namespace cv;
using namespace std;

#define CORE_COUNTNONZERO_ERROR_COUNT 1

#define MESSAGE_ERROR_COUNT "Count non zero elements returned by OpenCV function is incorrect."

#define sign(a) a > 0 ? 1 : a == 0 ? 0 : -1

const int FLOAT_TYPE [2] = {CV_32F, CV_64F};
const int INT_TYPE [5] = {CV_8U, CV_8S, CV_16U, CV_16S, CV_32S};

#define MAX_WIDTH 100
#define MAX_HEIGHT 100

class CV_CountNonZeroTest: public cvtest::BaseTest
{
 public:
	CV_CountNonZeroTest();
	~CV_CountNonZeroTest();

 protected:
	void run (int);

 private:
	 float eps_32; 
	 double eps_64; 
	 Mat src;
	 int current_type;
	
	 void generate_src_data(cv::Size size, int type);
	 void generate_src_data(cv::Size size, int type, int count_non_zero);
	 void generate_src_stat_data(cv::Size size, int type, int distribution);

	 int get_count_non_zero();

	 void print_information(int right, int result);
};

CV_CountNonZeroTest::CV_CountNonZeroTest(): eps_32(1e-8), eps_64(1e-16), src(Mat()), current_type(-1) {}
CV_CountNonZeroTest::~CV_CountNonZeroTest() {}

void CV_CountNonZeroTest::generate_src_data(cv::Size size, int type)
{
 src.create(size, CV_MAKETYPE(type, 1));

 for (size_t j = 0; j < size.width; ++j)
	for (size_t i = 0; i < size.height; ++i)
		switch (type)
		{
		 case CV_8U: { src.at<uchar>(i, j) = cv::randu<uchar>(); break; }
		 case CV_8S: { src.at<char>(i, j) = cv::randu<uchar>() - 128; break; }
		 case CV_16U: { src.at<ushort>(i, j) = cv::randu<ushort>(); break; }
		 case CV_16S: { src.at<short>(i, j) = cv::randu<short>(); break; }
		 case CV_32S: { src.at<int>(i, j) = cv::randu<int>(); break; }
		 case CV_32F: { src.at<float>(i, j) = cv::randu<float>(); break; }
		 case CV_64F: { src.at<double>(i, j) = cv::randu<double>(); break; }
		 default: break;
		}
}

void CV_CountNonZeroTest::generate_src_data(cv::Size size, int type, int count_non_zero)
{
 src = Mat::zeros(size, CV_MAKETYPE(type, 1));
 
 int n = 0; RNG& rng = ts->get_rng();

 while (n < count_non_zero)
 {
  size_t i = rng.next()%size.height, j = rng.next()%size.width;
	 
  switch (type)
  {
   case CV_8U: { if (!src.at<uchar>(i, j)) {src.at<uchar>(i, j) = cv::randu<uchar>(); n += abs(sign(src.at<uchar>(i, j)));} break; }
   case CV_8S: { if (!src.at<char>(i, j)) {src.at<char>(i, j) = cv::randu<uchar>() - 128; n += abs(sign(src.at<char>(i, j)));} break; }
   case CV_16U: { if (!src.at<ushort>(i, j)) {src.at<ushort>(i, j) = cv::randu<ushort>(); n += abs(sign(src.at<ushort>(i, j)));} break; }
   case CV_16S: { if (!src.at<short>(i, j)) {src.at<short>(i, j) = cv::randu<short>(); n += abs(sign(src.at<short>(i, j)));} break; }
   case CV_32S: { if (!src.at<int>(i, j)) {src.at<int>(i, j) = cv::randu<int>(); n += abs(sign(src.at<int>(i, j)));} break; }
   case CV_32F: { if (fabs(src.at<float>(i, j)) <= eps_32) {src.at<float>(i, j) = cv::randu<float>(); n += sign(fabs(src.at<float>(i, j)) > eps_32);} break; }
   case CV_64F: { if (fabs(src.at<double>(i, j)) <= eps_64) {src.at<double>(i, j) = cv::randu<double>(); n += sign(fabs(src.at<double>(i, j)) > eps_64);} break; }

   default: break;
  }
 }
 
}

void CV_CountNonZeroTest::generate_src_stat_data(cv::Size size, int type, int distribution)
{
 src.create(size, CV_MAKETYPE(type, 1));

 double mean = 0.0, sigma = 1.0;
 double left = -1.0, right = 1.0;

 RNG& rng = ts->get_rng();

 if (distribution == RNG::NORMAL) 
	 rng.fill(src, RNG::NORMAL, Scalar::all(mean), Scalar::all(sigma));
 else if (distribution == RNG::UNIFORM)
	 rng.fill(src, RNG::UNIFORM, Scalar::all(left), Scalar::all(right));
}

int CV_CountNonZeroTest::get_count_non_zero()
{
 int result = 0, channels = src.channels();

 for (size_t i = 0; i < src.rows; ++i)
 for (size_t j = 0; j < src.cols; ++j)

 if (current_type == CV_8U) result += abs(sign(src.at<uchar>(i, j)));
 
 else if (current_type == CV_8S) result += abs(sign(src.at<char>(i, j))); 

 else if (current_type == CV_16U) result += abs(sign(src.at<ushort>(i, j))); 

 else if (current_type == CV_16S) result += abs(sign(src.at<short>(i, j)));

 else if (current_type == CV_32S) result += abs(sign(src.at<int>(i, j)));

 else if (current_type == CV_32F) result += sign(fabs(src.at<float>(i, j)) > eps_32);

 else result += sign(fabs(src.at<double>(i, j)) > eps_64);

 return result;
}

void CV_CountNonZeroTest::print_information(int right, int result)
{
 cout << endl; cout << "Checking for the work of countNonZero function..." << endl; cout << endl;
 cout << "Type of Mat: "; 
 switch (current_type)
 {
  case 0: {cout << "CV_8U"; break;} 
  case 1: {cout << "CV_8S"; break;}
  case 2: {cout << "CV_16U"; break;}
  case 3: {cout << "CV_16S"; break;}
  case 4: {cout << "CV_32S"; break;}
  case 5: {cout << "CV_32F"; break;}
  case 6: {cout << "CV_64F"; break;}
  default: break;
 }
 cout << endl;
 cout << "Number of rows: " << src.rows << "   Number of cols: " << src.cols << endl;
 cout << "True count non zero elements: " << right << "   Result: " << result << endl; 
 cout << endl;
}

void CV_CountNonZeroTest::run(int)
{
 const size_t N = 1500;

 for (int k = 1; k <= 3; ++k)
 for (size_t i = 0; i < N; ++i)
 {
  RNG& rng = ts->get_rng();

  int w = rng.next()%MAX_WIDTH + 1, h = rng.next()%MAX_HEIGHT + 1;

  current_type = rng.next()%7;

  switch (k)
  {
   case 1: { 
	         generate_src_data(Size(w, h), current_type);
			 int right = get_count_non_zero(), result = countNonZero(src);
			 if (result != right)
			 {
			  cout << "Number of experiment: " << i << endl;
			  cout << "Method of data generation: RANDOM" << endl;
			  print_information(right, result);
			  CV_Error(CORE_COUNTNONZERO_ERROR_COUNT, MESSAGE_ERROR_COUNT);
			  return;
			 }

			 break;
		   }

   case 2: {
			int count_non_zero = rng.next()%(w*h);
	        generate_src_data(Size(w, h), current_type, count_non_zero);
			int result = countNonZero(src);
			if (result != count_non_zero)
			{
			 cout << "Number of experiment: " << i << endl;
			 cout << "Method of data generation: HALF-RANDOM" << endl;
			 print_information(count_non_zero, result);
			 CV_Error(CORE_COUNTNONZERO_ERROR_COUNT, MESSAGE_ERROR_COUNT);
			 return;
			}

			break;
		   }

   case 3: {
			int distribution = cv::randu<uchar>()%2;
			generate_src_stat_data(Size(w, h), current_type, distribution);
			int right = get_count_non_zero(), result = countNonZero(src);
			if (right != result)
			{
			 cout << "Number of experiment: " << i << endl;
			 cout << "Method of data generation: STATISTIC" << endl;
			 print_information(right, result);
			 CV_Error(CORE_COUNTNONZERO_ERROR_COUNT, MESSAGE_ERROR_COUNT);
			 return;
			}

			break;
		   }

   default: break;
  }
 }
}

// TEST (Core_CountNonZero, accuracy) { CV_CountNonZeroTest test; test.safe_run(); }